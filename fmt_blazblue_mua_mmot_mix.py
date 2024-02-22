from inc_noesis import *
import noesis
import rapi
import os

def registerNoesisTypes():
    handle = noesis.register("BLAZEBLUE", ".MUA")
    noesis.setHandlerTypeCheck(handle, noepyCheckType)
    noesis.setHandlerLoadModel(handle, noepyLoadModel)
    noesis.setHandlerWriteModel(handle, noepyWriteModel)
	#any noesis.NMSHAREDFL_* flags can be applied here, to affect the model which is handed off to the exporter.
	#adding noesis.NMSHAREDFL_FLATWEIGHTS_FORCE4 would force us to 4 weights per vert.
    noesis.setTypeSharedModelFlags(handle, noesis.NMSHAREDFL_REVERSEWINDING)
    #noesis.logPopup()
    #print("The log can be useful for catching debug prints from preview loads.\nBut don't leave it on when you release your script, or it will probably annoy people.")
    return 1

NOEPY_HEADER = "MUA"
headerdata = b'\x4D\x55\x41\x00\xEE\x03\x00\x00\x11\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

#check if it's this type based on the data
def noepyCheckType(data):
	if len(data) < 3:
		return 0
	bs = NoeBitStream(data)

	if bs.readBytes(3).decode("ASCII") != NOEPY_HEADER:
		return 0

	return 1

#read it
def noepyLoadModel(data, mdlList):
    #no need to explicitly free the context (created contexts are auto-freed after the handler), but DO NOT hold any references to it outside of this method
    ctx = rapi.rpgCreateContext()

    bs = NoeBitStream(data)

    #address
    addr = []
    count = []
	
    bc = 0
    while bc <= 16:
        bs.seek(0x20+bc*0x8, NOESEEK_ABS)
        addr.append(bs.readInt())
        bc += 1

    bc = 0
    while bc <= 16:
        bs.seek(0x24+bc*0x8, NOESEEK_ABS)
        count.append(bs.readInt())
        bc += 1
    
    SKAddress = addr[0]#Skeleton
    BAddress = addr[1]#bone
    MAddress = addr[2]#model
    PAddress = addr[3]#mesh
    MTAddress = addr[4]#matirial
    TAAddress = addr[5]#texture assign
    TNAddress = addr[6]#texture name Index
    ALAddress = addr[8]#animetion key frame list
    AAddress = addr[9]#animation key frame Value
    MPTAddress = addr[12]#meshes and parts Index table
    VAddress = addr[13]#vertext
    FAddress = addr[14]#face Triangle strip indices
    SIAddress = addr[15]#strng info,start from and length
    SAddress = addr[16]#string Name
    
    SKCount = count[0]
    boneCount = count[1]
    MCount = count[2]
    PCount = count[3]
    MTCount = count[4]
    TACount = count[5]
    TNCount = count[6]
    ALCount = count[8]
    MPTCount = count[12]
    VCount = count[13]
    TRCount = count[14]
    SICount = count[15]
		
	#Name(string)
    Name = []#skeleton,model,texture
    stringlength = []
    stringoffset = []
    for i in range(0, SICount):
            bs.seek(SIAddress, NOESEEK_ABS)
            stringoffset.append(bs.readUInt())
            bs.seek(SIAddress + 0x4, NOESEEK_ABS)
            stringlength.append(bs.readUInt())
            SIAddress += 0x10
            bs.seek(SAddress + stringoffset[i] , NOESEEK_ABS)
            Name.append(bs.readBytes(stringlength[i]).decode("Shift_JIS"))
            #bytes -> "Shift_JIS" -> utf8
            
    #material and texture
    MTIndex = []#Matirial texture index
    TNAIndex = []#Texture Name Assign Index
    TNIndex = []#Texture Name Index
    Texs = []
    Mat = []
    Mpath = noesis.getSelectedDirectory()
    for i in range(0, TNCount):#Texture Name Index
        bs.seek(TNAddress, NOESEEK_ABS)
        TNIndex.append(bs.readInt())
        Tpath = os.path.join(Mpath,Name[TNIndex[i]])
        Texs.append(rapi.loadExternalTex(Tpath))
        if Texs[i]:
            Texs[i].name = Name[TNIndex[i]]
        TNAddress += 0x10
    
    for i in range(0, TACount):#Texture Assign
        bs.seek(TAAddress,NOESEEK_ABS)
        MTIndex.append(bs.readInt())
        TNAIndex.append(bs.readInt())
        TAAddress += 0x20
        
    for i in range(0 ,MTCount):#Material
        bs.seek(MTAddress,NOESEEK_ABS)
        MTACount = bs.readInt()
        MTAOffset = bs.readInt()
        Mat.append(NoeMaterial(Name[TNIndex[TNAIndex[MTAOffset]]],Name[TNIndex[TNAIndex[MTAOffset]]]))
        if MTACount == 2:
            Mat[i].setOcclTexture(Name[TNIndex[TNAIndex[MTAOffset+1]]])
        MTAddress += 0x50
			
	#model
    MeshSkeletonIndex = []#Mesh Skeleton Index
    MPCount =[]#Mesh[i]mesh parts count
    MPoffeet =[]
    MVCount = []#Mesh[i] vertext count
    MVoffset = []
    MNIndex = []#Mesh Name Index
    MSRIndex = []#Mesh Scence Root Skeleton Index
    for i in range(0, MCount):
        bs.seek(MAddress, NOESEEK_ABS)
        MeshSkeletonIndex.append(int(bs.readFloat()))
        bs.seek(MAddress + 0x8, NOESEEK_ABS)
        MPCount.append(bs.readInt())
        MPoffeet.append(bs.readInt())
        MVCount.append(bs.readInt())
        MVoffset.append(bs.readInt())
        bs.seek(MAddress + 0xB4, NOESEEK_ABS)
        MNIndex.append(bs.readInt())
        MSRIndex.append(bs.readInt())
        MAddress += 0xc0
    
    #part
    PMatIndex = []#parts Matirial Index
    PFCount = []#parts face triangle list count
    PFoffset = []
    PEvb = []#parts evb value count
    PEoffset = []
    for i in range(0, PCount):
        bs.seek(PAddress, NOESEEK_ABS)
        PMatIndex.append(bs.readInt())
        PFCount.append(bs.readInt())
        PFoffset.append(bs.readInt())
        PEoffset.append(bs.readInt())
        PEvb.append(bs.readInt())
        PAddress += 0x20
    
    #bone
    bones = []
    skeletons = []
    SKoffset = []
    SKBcount = []
    SKBoneIndex = []
    KFcount = []#defult animation key frame count
    for sk in range(0, SKCount):
            bs.seek(SKAddress)
            SKoffset.append(bs.readUInt())
            SKBcount.append(bs.readUInt())
            SKAddress += 0x20
            for b in range(0, SKBcount[sk]):
                    bs.seek(BAddress, NOESEEK_ABS)
                    boneNameIndex = bs.readUInt()
                    boneType = bs.readUInt()
                    if boneType == 5:
                        SKBoneIndex.append(sk)
                    Tran = NoeVec3.fromBytes(bs.readBytes(12))
                    Rot = NoeAngles.toDegrees((NoeVec3.fromBytes(bs.readBytes(12))))
                    Scal = NoeVec3.fromBytes(bs.readBytes(12))
                    bs.seek(BAddress + 0x3C , NOESEEK_ABS)
                    bonePIndex = bs.readInt()
                    bs.seek(BAddress + 0x48 , NOESEEK_ABS)
                    Mat44 = NoeMat44.fromBytes(bs.readBytes(0x40), NOE_LITTLEENDIAN )
                    boneMat = Mat44.toMat43()
                    bs.seek(BAddress + 0x108 , NOESEEK_ABS)
                    KFcount.append(bs.readUInt())
                    bones.append(NoeBone(b,Name[boneNameIndex], boneMat, None , bonePIndex))
                    BAddress += 0x130
            for b in range(0, SKBcount[sk]):
                    p = bones[b].parentIndex
                    if p != -1:
                        bones[b].setMatrix(bones[b].getMatrix() * bones[p].getMatrix() )
            skeletons.append(bones)
            bones = []
            
    #meshes and parts Index table
    MeshIndex = []
    MpartIndex = []
    for i in range(0, PCount):
        bs.seek(MPTAddress , NOESEEK_ABS)
        MeshIndex.append(bs.readUInt())
        MpartIndex.append(bs.readUInt())
        MPTAddress += 0x20
    
    #model Consturct
    PIndex = 0
    for i in range(0, MCount):
        bs.seek(VAddress , NOESEEK_ABS)
        VBuffer = bs.readBytes(MVCount[i] * 0x50)
        rapi.rpgOptimize()
        rapi.rpgBindPositionBufferOfs(VBuffer, noesis.RPGEODATA_FLOAT, 80, 0)
        rapi.rpgBindNormalBufferOfs(VBuffer,noesis.RPGEODATA_INT, 80, 12)
        rapi.rpgBindTangentBufferOfs(VBuffer,noesis.RPGEODATA_INT, 80, 24)
        rapi.rpgBindUV1BufferOfs(VBuffer, noesis.RPGEODATA_FLOAT, 80, 36)
        rapi.rpgBindColorBufferOfs(VBuffer, noesis.RPGEODATA_UBYTE, 80, 52,4)
        rapi.rpgBindBoneIndexBufferOfs(VBuffer, noesis.RPGEODATA_FLOAT, 80, 56,3)
        rapi.rpgBindBoneWeightBufferOfs(VBuffer, noesis.RPGEODATA_FLOAT, 80, 68,3)
        for j in range(0, MPCount[i]):
            bs.seek(FAddress + PFoffset[PIndex] * 0x2, NOESEEK_ABS)
            FBuffer = bs.readBytes(PFCount[PIndex] * 0x2)
            rapi.rpgSetMaterial(Mat[PMatIndex[PIndex]].name)
            rapi.rpgCommitTriangles(FBuffer, noesis.RPGEODATA_USHORT, PFCount[PIndex], noesis.RPGEO_TRIANGLE_STRIP, 1)
            PIndex += 1
        VAddress += MVCount[i] * 0x50
        mdl = rapi.rpgConstructModelAndSort()
        mdlList.append(mdl)
        rapi.rpgClearBufferBinds()
        rapi.rpgReset()
        mdlList[i].meshes[0].setName(Name[MNIndex[i]])
        mdlList[i].setBones(skeletons[MeshSkeletonIndex[i]])
        
    #animetion
    anims = []
    kfBones = []
    translationKeys = []
    rotationKeys = []
    shearKeys = []
    scaleKeys = []
    boneIndex = 0
    for i in range(0,SKCount):
        for j in range(0, SKBcount[i]):
            if KFcount[boneIndex]:
                bs.seek(ALAddress + 0x4, NOESEEK_ABS)
                trankeys = bs.readUInt()
                bs.seek(ALAddress + 0x14, NOESEEK_ABS)
                rotkeys = bs.readUInt()
                bs.seek(ALAddress + 0x24, NOESEEK_ABS)
                shrkeys = bs.readUInt()
                bs.seek(ALAddress + 0x34, NOESEEK_ABS)
                scalkeys = bs.readUInt()
                for k in range(0,trankeys):
                    bs.seek(AAddress, NOESEEK_ABS)
                    tran = NoeVec3.fromBytes(bs.readBytes(12))
                    bs.seek(AAddress + 0x10, NOESEEK_ABS)
                    time = bs.readUInt()
                    translationKeys.append(NoeKeyFramedValue(time,tran))
                    AAddress += 0x20
                for l in range(0,rotkeys):
                    bs.seek(AAddress, NOESEEK_ABS)
                    rot = NoeAngles.fromBytes(bs.readBytes(12))
                    rot = rot.toDegrees()
                    bs.seek(AAddress + 0x10, NOESEEK_ABS)
                    time = bs.readUInt()
                    rotationKeys.append(NoeKeyFramedValue(time,rot))
                    AAddress += 0x20
                for m in range(0,shrkeys):
                    bs.seek(AAddress, NOESEEK_ABS)
                    shr = NoeQuat.fromBytes(bs.readBytes(16))
                    bs.seek(AAddress + 0x10, NOESEEK_ABS)
                    time = bs.readUInt()
                    shearKeys.append(NoeKeyFramedValue(time,shr))
                    AAddress += 0x20
                for n in range(0,scalkeys):
                    bs.seek(AAddress, NOESEEK_ABS)
                    scal = NoeVec3.fromBytes(bs.readBytes(12))
                    bs.seek(AAddress + 0x10, NOESEEK_ABS)
                    time = bs.readUInt()
                    scaleKeys.append(NoeKeyFramedValue(time,scal))
                    AAddress += 0x20
                kfBones.append(NoeKeyFramedBone(j))
                kfBones[j].setRotation(rotationKeys,noesis.NOEKF_ROTATION_EULER_XYZ_3,noesis.NOEKF_INTERPOLATE_LINEAR)
                kfBones[j].setTranslation(translationKeys,noesis.NOEKF_TRANSLATION_VECTOR_3,noesis.NOEKF_INTERPOLATE_LINEAR)
                kfBones[j].setScale(scaleKeys,noesis.NOEKF_SCALE_VECTOR_3,noesis.NOEKF_INTERPOLATE_LINEAR)
                translationKeys = []
                rotationKeys = []
                shearKeys = []
                scaleKeys = []
                ALAddress += 0x40
            boneIndex += 1
        anims.append(NoeKeyFramedAnim("DefultPose", skeletons[i], kfBones, frameRate = 1, flags = 0))
        kfBones = []
        for o in range(0, MCount):
            if MeshSkeletonIndex[o] == i:
                mdlList[o].setAnims(anims)
        anims = []
                
        
    #Import animetion
    ab = NoeBitStream(rapi.loadPairedFileOptional("model motion",".mmot"))
    if ab.data != None:
        addr2 = []
        count2 = []
	
        bc = 0
        while bc <= 10:
            ab.seek(0x20+bc*0x10, NOESEEK_ABS)
            addr2.append(ab.readInt())
            bc += 1

        bc = 0
        while bc <= 10:
            ab.seek(0x24+bc*0x10, NOESEEK_ABS)
            count2.append(ab.readInt())
            bc += 1
    
        ABCount = count2[1]
        ALAddress = addr2[2]#animetion key frame list
        AAddress = addr2[3]#animation key frame Value
        LMAddress = addr2[4]#linked mesh
        LMCount = count2[4]
        SIAddress2 = addr2[8]#string info
        SICount2 = count2[8]
        SAddress2 = addr2[9]#string
	
        stringlength2 = []
        stringoffset2 = []
        Name2 = []
        anims = []
    
        #Name(string)
        for i in range(0, SICount2):
                ab.seek(SIAddress2, NOESEEK_ABS)
                stringoffset2.append(ab.readUInt())
                ab.seek(SIAddress2 + 0x4, NOESEEK_ABS)
                stringlength2.append(ab.readUInt())
                SIAddress2 += 0x10
    
        for i in range(0, SICount2):
                ab.seek(SAddress2 + stringoffset2[i], NOESEEK_ABS)
                Name2.append(bs.readBytes(stringlength2[i]).decode("Shift_JIS"))
                
        #bone
        bones = []
        for b in range(0, ABCount):
                bs.seek(BAddress, NOESEEK_ABS)
                Mat44 = NoeMat44.fromBytes(bs.readBytes(0x40), NOE_LITTLEENDIAN )
                boneMat = Mat44.toMat43()
                bones.append( NoeBone(b,str(b), boneMat, None , -1) )
                BAddress += 0xE0
    
        #animation
        translationKeys = []
        rotationKeys = []
        shearKeys = []
        scaleKeys = []
        kfBones = []
        for i in range(0,ABCount):
                ab.seek(ALAddress + 0x4, NOESEEK_ABS)
                trankeys = ab.readInt()
                ab.seek(ALAddress + 0x14, NOESEEK_ABS)
                rotkeys = ab.readInt()
                ab.seek(ALAddress + 0x24, NOESEEK_ABS)
                shrkeys = ab.readInt()
                ab.seek(ALAddress + 0x34, NOESEEK_ABS)
                scalkeys = ab.readInt()
                for j in range(0,trankeys):
                    ab.seek(AAddress, NOESEEK_ABS)
                    tran = NoeVec3.fromBytes(ab.readBytes(12))
                    ab.seek(AAddress + 0x10, NOESEEK_ABS)
                    time = ab.readUInt()
                    translationKeys.append(NoeKeyFramedValue(time,tran))
                    AAddress += 0x20
                for k in range(0,rotkeys):
                    ab.seek(AAddress, NOESEEK_ABS)
                    rot = NoeAngles.fromBytes(ab.readBytes(12))
                    rot = rot.toDegrees()
                    ab.seek(AAddress + 0x10, NOESEEK_ABS)
                    time = ab.readUInt()
                    rotationKeys.append(NoeKeyFramedValue(time,rot))
                    AAddress += 0x20
                for l in range(0,shrkeys):
                    ab.seek(AAddress, NOESEEK_ABS)
                    shr = NoeQuat.fromBytes(ab.readBytes(16))
                    ab.seek(AAddress + 0x10, NOESEEK_ABS)
                    time = ab.readUInt()
                    shearKeys.append(NoeKeyFramedValue(time,shr))
                    AAddress += 0x20
                for m in range(0,scalkeys):
                    ab.seek(AAddress, NOESEEK_ABS)
                    scal = NoeVec3.fromBytes(ab.readBytes(12))
                    ab.seek(AAddress + 0x10, NOESEEK_ABS)
                    time = ab.readUInt()
                    scaleKeys.append(NoeKeyFramedValue(time,scal))
                    AAddress += 0x20
                kfBones.append(NoeKeyFramedBone(i))
                kfBones[i].setRotation(rotationKeys,noesis.NOEKF_ROTATION_EULER_XYZ_3,noesis.NOEKF_INTERPOLATE_LINEAR)
                kfBones[i].setTranslation(translationKeys,noesis.NOEKF_TRANSLATION_VECTOR_3,noesis.NOEKF_INTERPOLATE_LINEAR)
                kfBones[i].setScale(scaleKeys,noesis.NOEKF_SCALE_VECTOR_3,noesis.NOEKF_INTERPOLATE_LINEAR)
                translationKeys = []
                rotationKeys = []
                shearKeys = []
                scaleKeys = []
                ALAddress += 0x40
        anims.append(NoeKeyFramedAnim(Name2[0], bones, kfBones, frameRate = 1, flags = 0))
        #assign mesh
        for i in range(0,LMCount):
            ab.seek(LMAddress + 0x4, NOESEEK_ABS)
            LMNIndex = ab.readUInt()
            LMAddress += 0x20
            for j in range(0,MCount):
                if Name2[LMNIndex] == str(mdlList[j].meshes[0].name):
                    mdlList[j].setAnims(anims)
    
    rapi.setPreviewOption("drawAllModels","1")
    #rapi.setPreviewOption("setAngOfs", "0 90 90")
    
    return 1
    

def noepyWriteModel(mdl, writer):
    writer = NoeBitStream()
    
    open("somefile.MUA", "wb+").write(writer.getBuffer())
    writer.writeBytes(headerdata)
    
    return 1